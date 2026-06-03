"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { User, Lock, Shield, HardDrive, Bell, Save, Eye, EyeOff } from "lucide-react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { formatBytes, formatPercent } from "@/lib/utils";
import toast from "react-hot-toast";

export default function SettingsPage() {
  const { user, updateUser } = useAuthStore();
  const [activeTab, setActiveTab] = useState<"profile"|"security"|"storage">("profile");

  // Profile form
  const [profile, setProfile] = useState({
    full_name: user?.full_name ?? "",
    bio: "",
    avatar_url: user?.avatar_url ?? "",
  });

  // Password form
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "" });
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);

  const updateProfile = useMutation({
    mutationFn: () => authApi.updateProfile(profile),
    onSuccess: ({ data }) => {
      updateUser(data);
      toast.success("Profile updated!");
    },
    onError: () => toast.error("Failed to update profile"),
  });

  const changePassword = useMutation({
    mutationFn: () => authApi.changePassword(passwords),
    onSuccess: () => {
      toast.success("Password changed! Please log in again.");
      setPasswords({ current_password: "", new_password: "" });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? "Failed to change password"),
  });

  if (!user) return null;

  const TABS = [
    { id: "profile",  label: "Profile",  icon: User },
    { id: "security", label: "Security", icon: Shield },
    { id: "storage",  label: "Storage",  icon: HardDrive },
  ] as const;

  const usedPct = (user.storage_used_bytes / user.storage_quota_bytes) * 100;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Settings</h2>
        <p className="text-slate-400 text-sm mt-0.5">Manage your account and preferences</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 glass rounded-xl p-1 w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === id
                ? "bg-brand-600 text-white shadow-glow"
                : "text-slate-400 hover:text-white"
            }`}>
            <Icon className="w-4 h-4"/>{label}
          </button>
        ))}
      </div>

      {/* Profile tab */}
      {activeTab === "profile" && (
        <div className="card space-y-5">
          <h3 className="text-base font-semibold text-white">Profile Information</h3>

          {/* Avatar */}
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-brand-600/20 border border-brand-500/30 flex items-center justify-center">
              <span className="text-2xl font-bold text-brand-300">
                {user.username?.[0]?.toUpperCase()}
              </span>
            </div>
            <div>
              <p className="text-white font-medium">{user.username}</p>
              <p className="text-slate-400 text-sm">{user.email}</p>
              <p className="text-xs text-slate-500 mt-0.5 capitalize">{user.role} · {user.is_verified ? "Verified" : "Unverified"}</p>
            </div>
          </div>

          <div>
            <label className="label">Full Name</label>
            <input value={profile.full_name} onChange={e => setProfile({...profile, full_name: e.target.value})}
              placeholder="Your full name" className="input"/>
          </div>

          <div>
            <label className="label">Avatar URL</label>
            <input value={profile.avatar_url} onChange={e => setProfile({...profile, avatar_url: e.target.value})}
              placeholder="https://…" className="input"/>
          </div>

          <div className="pt-2">
            <button onClick={() => updateProfile.mutate()}
              disabled={updateProfile.isPending}
              className="btn-primary gap-2">
              <Save className="w-4 h-4"/>
              {updateProfile.isPending ? "Saving…" : "Save Changes"}
            </button>
          </div>

          {/* Read-only info */}
          <div className="border-t border-surface-border pt-4 space-y-3">
            <h4 className="text-sm font-medium text-slate-400">Account Info</h4>
            {[
              ["User ID",    user.id],
              ["Email",      user.email],
              ["Username",   `@${user.username}`],
              ["Role",       user.role],
              ["Verified",   user.is_verified ? "Yes" : "No"],
              ["Member since", user.created_at ? new Date(user.created_at).toLocaleDateString() : "—"],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between text-sm">
                <span className="text-slate-500">{label}</span>
                <span className="text-slate-300 font-mono text-xs truncate max-w-48">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Security tab */}
      {activeTab === "security" && (
        <div className="space-y-5">
          <div className="card space-y-5">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Lock className="w-4 h-4 text-brand-400"/> Change Password
            </h3>

            <div>
              <label className="label">Current Password</label>
              <div className="relative">
                <input type={showCurrent ? "text" : "password"}
                  value={passwords.current_password}
                  onChange={e => setPasswords({...passwords, current_password: e.target.value})}
                  placeholder="••••••••" className="input pr-11"/>
                <button type="button" onClick={() => setShowCurrent(!showCurrent)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                  {showCurrent ? <EyeOff className="w-4 h-4"/> : <Eye className="w-4 h-4"/>}
                </button>
              </div>
            </div>

            <div>
              <label className="label">New Password</label>
              <div className="relative">
                <input type={showNew ? "text" : "password"}
                  value={passwords.new_password}
                  onChange={e => setPasswords({...passwords, new_password: e.target.value})}
                  placeholder="Min 8 chars, uppercase + digit" className="input pr-11"/>
                <button type="button" onClick={() => setShowNew(!showNew)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                  {showNew ? <EyeOff className="w-4 h-4"/> : <Eye className="w-4 h-4"/>}
                </button>
              </div>
            </div>

            <button onClick={() => changePassword.mutate()}
              disabled={changePassword.isPending || !passwords.current_password || !passwords.new_password}
              className="btn-primary gap-2">
              <Lock className="w-4 h-4"/>
              {changePassword.isPending ? "Changing…" : "Change Password"}
            </button>
          </div>

          <div className="card space-y-4">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Shield className="w-4 h-4 text-emerald-400"/> Security Info
            </h3>
            {[
              ["Encryption",      "AES-256-GCM per chunk"],
              ["Hashing",         "SHA-256 (files & chunks)"],
              ["Auth",            "JWT + refresh token rotation"],
              ["Token TTL",       "24h access / 30d refresh"],
              ["Rate limiting",   "IP-based via Redis"],
              ["IPFS Encryption", "Each chunk encrypted before upload"],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between text-sm">
                <span className="text-slate-400">{label}</span>
                <span className="badge-green text-xs">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Storage tab */}
      {activeTab === "storage" && (
        <div className="card space-y-5">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-purple-400"/> Storage Details
          </h3>

          {/* Big gauge */}
          <div className="text-center py-4">
            <div className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-purple-400 mb-1">
              {formatPercent(usedPct)}
            </div>
            <div className="text-slate-400 text-sm">of your quota used</div>
          </div>

          <div className="w-full h-3 bg-surface-hover rounded-full overflow-hidden">
            <div className="h-full progress-fill rounded-full transition-all duration-700"
              style={{ width: `${Math.min(usedPct, 100)}%` }}/>
          </div>

          <div className="flex justify-between text-sm">
            <span className="text-slate-400">{formatBytes(user.storage_used_bytes)} used</span>
            <span className="text-slate-400">{formatBytes(user.storage_quota_bytes)} total</span>
          </div>

          <div className="border-t border-surface-border pt-4 space-y-3">
            {[
              ["Plan",           "Free"],
              ["Quota",          formatBytes(user.storage_quota_bytes)],
              ["Used",           formatBytes(user.storage_used_bytes)],
              ["Available",      formatBytes(Math.max(0, user.storage_quota_bytes - user.storage_used_bytes))],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between text-sm">
                <span className="text-slate-500">{label}</span>
                <span className="text-white font-medium">{value}</span>
              </div>
            ))}
          </div>

          <div className="bg-brand-600/10 border border-brand-500/20 rounded-xl p-4 text-sm text-brand-300">
            💡 Deduplication is active — identical chunks across files are stored once, saving storage automatically.
          </div>
        </div>
      )}
    </div>
  );
}
