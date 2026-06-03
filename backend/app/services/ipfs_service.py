"""
IPFS Service via Pinata
Upload, retrieve, and pin encrypted chunks
"""
import asyncio
import io
import logging
from typing import Dict, List, Optional, Tuple

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class IPFSService:
    """
    Pinata-backed IPFS service.
    Handles pin, retrieve, unpin, and batch operations.
    """

    BASE = "https://api.pinata.cloud"
    GATEWAY = settings.PINATA_GATEWAY

    def __init__(self):
        self.jwt = settings.PINATA_JWT
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.jwt}"}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=180, connect=15)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ── Upload ────────────────────────────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def pin_bytes(
        self,
        data: bytes,
        filename: str,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Pin raw bytes to IPFS. Returns Pinata response dict with IpfsHash."""
        if not self.jwt:
            # Return mock CID when Pinata not configured (dev mode)
            import hashlib
            mock_cid = "bafybei" + hashlib.sha256(data).hexdigest()[:38]
            logger.warning(f"Pinata not configured — mock CID: {mock_cid}")
            return {"IpfsHash": mock_cid, "PinSize": len(data)}

        session = await self._get_session()
        form = aiohttp.FormData()
        form.add_field(
            "file",
            io.BytesIO(data),
            filename=filename,
            content_type="application/octet-stream",
        )
        options = {"cidVersion": 1}
        import json
        form.add_field("pinataOptions", json.dumps(options))
        if metadata:
            form.add_field("pinataMetadata", json.dumps({"name": filename, "keyvalues": metadata}))

        async with session.post(
            f"{self.BASE}/pinning/pinFileToIPFS",
            headers=self._headers,
            data=form,
        ) as resp:
            if resp.status not in (200, 201):
                body = await resp.text()
                raise RuntimeError(f"Pinata pin failed {resp.status}: {body}")
            result = await resp.json()
            logger.debug(f"Pinned {filename}: {result['IpfsHash']}")
            return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def retrieve_bytes(self, cid: str) -> bytes:
        """Retrieve bytes from IPFS gateway by CID."""
        session = await self._get_session()
        url = f"{self.GATEWAY}{cid}"
        async with session.get(url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"IPFS retrieve failed for {cid}: {resp.status}")
            return await resp.read()

    async def unpin(self, cid: str) -> bool:
        """Unpin a CID from Pinata."""
        if not self.jwt:
            return True
        session = await self._get_session()
        try:
            async with session.delete(
                f"{self.BASE}/pinning/unpin/{cid}",
                headers=self._headers,
            ) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f"Unpin failed for {cid}: {e}")
            return False

    # ── Batch ─────────────────────────────────────────────────────────────────
    async def pin_chunks_batch(
        self,
        chunks: List[Tuple[bytes, str]],  # (data, filename)
        max_concurrent: int = 5,
        file_id: str = "",
    ) -> List[Dict]:
        """Upload multiple chunks concurrently. Returns list of Pinata responses."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _upload_one(data: bytes, fname: str, idx: int) -> Tuple[int, Dict]:
            async with semaphore:
                result = await self.pin_bytes(
                    data, fname,
                    metadata={"file_id": file_id, "chunk_index": str(idx)},
                )
                return idx, result

        tasks = [_upload_one(d, f, i) for i, (d, f) in enumerate(chunks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        ordered = [None] * len(chunks)
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Chunk upload error: {r}")
                raise r
            idx, resp = r
            ordered[idx] = resp
        return ordered

    async def retrieve_chunks_batch(
        self,
        cids: List[str],
        max_concurrent: int = 5,
    ) -> Dict[str, bytes]:
        """Retrieve multiple chunks by CID concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _get_one(cid: str) -> Tuple[str, bytes]:
            async with semaphore:
                data = await self.retrieve_bytes(cid)
                return cid, data

        tasks = [_get_one(cid) for cid in cids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out: Dict[str, bytes] = {}
        for r in results:
            if not isinstance(r, Exception):
                cid, data = r
                out[cid] = data
        return out

    async def test_auth(self) -> bool:
        """Test Pinata JWT authentication."""
        if not self.jwt:
            return False
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.BASE}/data/testAuthentication",
                headers=self._headers,
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_gateway_url(self, cid: str) -> str:
        return f"{self.GATEWAY}{cid}"


# Singleton
ipfs_service = IPFSService()
