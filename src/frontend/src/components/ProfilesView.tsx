import { useEffect, useRef, useState } from "react";
import { Building2, Camera, Check, Link2, Mail, ShieldCheck, Sparkles, Trash2, Upload, UserCheck, Users } from "lucide-react";
import { formatCreditsBdtUsd } from "../services/payment";
import { ModelTier, TaskType, UserProfile } from "../types/ai";
import { UserAvatar } from "./UserAvatar";

const PRESET_AVATARS = [
  { label: "AI Dev", url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=256&auto=format&fit=crop&q=80" },
  { label: "Creator", url: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=256&auto=format&fit=crop&q=80" },
  { label: "Scientist", url: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=256&auto=format&fit=crop&q=80" },
  { label: "Cyber", url: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=256&auto=format&fit=crop&q=80" },
  { label: "3D Digital", url: "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?w=256&auto=format&fit=crop&q=80" },
];

interface ProfilesViewProps {
  user: UserProfile | null;
  profiles: UserProfile[];
  onSaveProfile: (payload: Partial<UserProfile>) => Promise<void>;
}

export function ProfilesView({
  user,
  profiles,
  onSaveProfile,
}: ProfilesViewProps) {
  const [displayName, setDisplayName] = useState(user?.display_name || "");
  const [avatar, setAvatar] = useState(user?.avatar || "");
  const [avatarError, setAvatarError] = useState("");
  const [email, setEmail] = useState(user?.email || "");
  const [firstName, setFirstName] = useState(user?.first_name || "");
  const [lastName, setLastName] = useState(user?.last_name || "");
  const [roleTitle, setRoleTitle] = useState(user?.role_title || "AI Builder");
  const [organization, setOrganization] = useState(user?.organization || "");
  const [bio, setBio] = useState(user?.bio || "");
  const [defaultTier, setDefaultTier] = useState<ModelTier>(user?.default_tier || "flash");
  const [defaultTask, setDefaultTask] = useState<TaskType>(user?.default_task || "chat");
  const [defaultSystemPrompt, setDefaultSystemPrompt] = useState(user?.default_system_prompt || "");
  const [avatarUrlInput, setAvatarUrlInput] = useState("");
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!user) return;
    setDisplayName(user.display_name || "");
    setAvatar(user.avatar || "");
    setEmail(user.email || "");
    setFirstName(user.first_name || "");
    setLastName(user.last_name || "");
    setRoleTitle(user.role_title || "AI Builder");
    setOrganization(user.organization || "");
    setBio(user.bio || "");
    setDefaultTier(user.default_tier || "flash");
    setDefaultTask(user.default_task || "chat");
    setDefaultSystemPrompt(user.default_system_prompt || "");
  }, [user]);

  const handleAvatarUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (e.target) e.target.value = "";
    if (!file) return;
    setAvatarError("");
    if (!file.type.startsWith("image/")) {
      setAvatarError("Please select a valid image file (PNG, JPG, WebP, GIF, SVG).");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setAvatarError("Avatar image must be under 5 MB.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const rawUrl = reader.result as string;
      const img = new Image();
      img.onload = () => {
        try {
          const maxDim = 256;
          let w = img.width;
          let h = img.height;
          if (w > maxDim || h > maxDim) {
            if (w > h) {
              h = Math.round((h * maxDim) / w);
              w = maxDim;
            } else {
              w = Math.round((w * maxDim) / h);
              h = maxDim;
            }
          }
          const canvas = document.createElement("canvas");
          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext("2d");
          if (ctx) {
            ctx.drawImage(img, 0, 0, w, h);
            let optimized = "";
            try {
              optimized = canvas.toDataURL("image/jpeg", 0.90);
            } catch {
              optimized = canvas.toDataURL();
            }
            if (optimized) {
              setAvatar(optimized);
              void onSaveProfile({ avatar: optimized });
              return;
            }
          }
        } catch {
          // Fallback to raw data url if canvas manipulation fails
        }
        setAvatar(rawUrl);
        void onSaveProfile({ avatar: rawUrl });
      };
      img.onerror = () => {
        setAvatar(rawUrl);
        void onSaveProfile({ avatar: rawUrl });
      };
      img.src = rawUrl;
    };
    reader.onerror = () => {
      setAvatarError("Failed to read image file.");
    };
    reader.readAsDataURL(file);
  };

  const handleApplyAvatarUrl = async () => {
    const raw = avatarUrlInput.trim();
    if (!raw) return;
    setAvatarError("");
    setAvatar(raw);
    setAvatarUrlInput("");
    await onSaveProfile({ avatar: raw });
  };

  const handleSelectPreset = async (presetUrl: string) => {
    setAvatarError("");
    setAvatar(presetUrl);
    await onSaveProfile({ avatar: presetUrl });
  };

  const handleRemoveAvatar = async () => {
    setAvatar("");
    setAvatarError("");
    if (fileInputRef.current) fileInputRef.current.value = "";
    await onSaveProfile({ avatar: "" });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    try {
      await onSaveProfile({
        display_name: displayName.trim(),
        avatar: avatar.trim(),
        email: email.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        role_title: roleTitle.trim() || "AI Builder",
        organization: organization.trim(),
        bio: bio.trim(),
        default_tier: defaultTier,
        default_task: defaultTask,
        default_system_prompt: defaultSystemPrompt.trim(),
      });
    } finally {
      setSaving(false);
    }
  };

  const roleBadge = user?.is_superuser ? "Superuser" : user?.is_staff ? "Staff" : "Member";

  return (
    <div className="space-y-4">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleAvatarUpload}
        className="hidden"
      />

      {/* Account Summary Banner (sm) */}
      <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-xs dark:shadow-none">
        <div className="flex items-center gap-3">
          <div className="relative group shrink-0">
            <UserAvatar
              avatar={avatar}
              name={user?.display_name || user?.username}
              sizeClass="w-12 h-12"
              roundedClass="rounded-xl"
              textSizeClass="text-sm"
              className="ring-2 ring-indigo-500/40"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              title="Click to change profile avatar"
              className="absolute inset-0 rounded-xl bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center text-white transition-opacity cursor-pointer"
            >
              <Camera className="w-4 h-4" />
            </button>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-display font-bold text-base text-slate-900 dark:text-white">
                {user?.display_name || `@${user?.username || "user"}`}
              </h2>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-mono text-[10px]">
                <ShieldCheck className="w-3 h-3" />
                {roleBadge}
              </span>
            </div>
            <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
              @{user?.username} · {user?.role_title || "AI Builder"}
              {user?.organization ? ` @ ${user.organization}` : ""}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <span className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-cyan-700 dark:text-cyan-300">
            {user?.plan_name || "Free"}
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200">
            {formatCreditsBdtUsd(user?.remaining_credits)}
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200">
            {user?.conversation_count ?? 0} chats
          </span>
        </div>
      </div>

      {/* Editable Profile Settings Form */}
      <form
        onSubmit={handleSubmit}
        className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 shadow-xs dark:shadow-none"
      >
        <div className="flex items-center justify-between">
          <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-indigo-600 dark:text-cyan-400" />
            <span>Profile &amp; Studio Preferences</span>
          </h3>
          <button
            type="submit"
            disabled={saving}
            className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
          >
            <Check className="w-3.5 h-3.5" />
            <span>{saving ? "Saving..." : "Save Profile"}</span>
          </button>
        </div>

        {/* Profile Avatar Management Card */}
        <div className="rounded-xl p-3 bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="relative group shrink-0">
                <UserAvatar
                  avatar={avatar}
                  name={user?.display_name || user?.username}
                  sizeClass="w-12 h-12"
                  roundedClass="rounded-xl"
                  textSizeClass="text-sm"
                  className="ring-2 ring-indigo-500/50"
                />
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  <Camera className="w-3.5 h-3.5 text-indigo-500" />
                  <span>Profile Avatar</span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Upload a photo (PNG, JPG, WebP, GIF, up to 5MB), enter a direct image URL, or choose a preset.
                </p>
                {avatarError && <p className="text-[11px] text-rose-500 mt-0.5">{avatarError}</p>}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-500/15 hover:bg-indigo-100 dark:hover:bg-indigo-500/25 text-indigo-700 dark:text-indigo-300 text-xs font-semibold flex items-center gap-1.5 border border-indigo-200 dark:border-indigo-500/30 transition cursor-pointer"
              >
                <Upload className="w-3.5 h-3.5" />
                <span>{avatar ? "Change Avatar" : "Upload Photo"}</span>
              </button>
              {avatar && (
                <button
                  type="button"
                  onClick={handleRemoveAvatar}
                  className="px-2.5 py-1.5 rounded-lg bg-rose-50 dark:bg-rose-500/10 hover:bg-rose-100 dark:hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 text-xs font-semibold flex items-center gap-1 border border-rose-200 dark:border-rose-500/20 transition cursor-pointer"
                  title="Remove custom avatar and use initials"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Remove</span>
                </button>
              )}
            </div>
          </div>

          {/* Quick Presets & Direct URL Input */}
          <div className="pt-2 border-t border-slate-200/70 dark:border-slate-800/70 flex flex-wrap items-center justify-between gap-2.5">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 mr-1 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-cyan-500" />
                Presets:
              </span>
              {PRESET_AVATARS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => handleSelectPreset(preset.url)}
                  title={`Use ${preset.label} preset`}
                  className="px-2 py-1 rounded-md text-[10px] font-medium bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-cyan-500 hover:text-cyan-600 dark:hover:text-cyan-400 transition flex items-center gap-1 cursor-pointer"
                >
                  <img src={preset.url} alt={preset.label} className="w-3.5 h-3.5 rounded-full object-cover" />
                  <span>{preset.label}</span>
                </button>
              ))}
            </div>

            <div className="flex items-center gap-1.5 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <Link2 className="w-3 h-3 text-slate-400 absolute left-2 top-2" />
                <input
                  type="url"
                  value={avatarUrlInput}
                  onChange={(e) => setAvatarUrlInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void handleApplyAvatarUrl();
                    }
                  }}
                  placeholder="Or paste image URL..."
                  className="w-full pl-6 pr-2 py-1 rounded-md text-[11px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400"
                />
              </div>
              <button
                type="button"
                onClick={handleApplyAvatarUrl}
                disabled={!avatarUrlInput.trim()}
                className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-200 dark:bg-slate-800 hover:bg-cyan-600 hover:text-white dark:hover:bg-cyan-600 text-slate-700 dark:text-slate-200 disabled:opacity-40 transition cursor-pointer"
              >
                Apply
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <div>
            <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Tblinc Builder"
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">Role Title</label>
            <input
              type="text"
              value={roleTitle}
              onChange={(e) => setRoleTitle(e.target.value)}
              placeholder="AI Builder"
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">First Name</label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">Last Name</label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">Organization</label>
            <input
              type="text"
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
              placeholder="tblinc Studio"
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">Default Model Tier</label>
            <select
              value={defaultTier}
              onChange={(e) => setDefaultTier(e.target.value as ModelTier)}
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
            >
              <option value="flash">tblinc Flash</option>
              <option value="pro">tblinc Pro</option>
              <option value="advance">tblinc Advance</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">Default Studio Mode</label>
            <select
              value={defaultTask}
              onChange={(e) => setDefaultTask(e.target.value as TaskType)}
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
            >
              <option value="chat">AI Chat</option>
              <option value="images">Create Images</option>
              <option value="video">Create Videos</option>
              <option value="code">Create Code</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">Default System Prompt</label>
            <input
              type="text"
              value={defaultSystemPrompt}
              onChange={(e) => setDefaultSystemPrompt(e.target.value)}
              placeholder="Optional assistant instruction..."
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>
        </div>

        <div>
          <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">Bio</label>
          <textarea
            rows={2}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder="Short bio or engineering focus..."
            className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-2.5 text-xs text-slate-900 dark:text-slate-100"
          />
        </div>
      </form>

      {/* Workspace Profiles Directory (compact sm cards) */}
      <div className="space-y-2.5">
        <h3 className="font-display font-semibold text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5 px-1">
          <Users className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
          <span>Workspace Profiles ({profiles.length})</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {profiles.map((p) => {
            const isSelf = p.id === user?.id;
            return (
              <div
                key={p.id}
                className={`rounded-xl p-3.5 border bg-white/90 dark:bg-slate-900/65 space-y-2 shadow-xs dark:shadow-none ${
                  isSelf ? "border-cyan-500/50" : "border-slate-200 dark:border-slate-800"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <UserAvatar
                      avatar={p.avatar}
                      name={p.display_name || p.username}
                      sizeClass="w-8 h-8"
                      roundedClass="rounded-lg"
                      textSizeClass="text-xs"
                      className="bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300"
                    />
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                        {p.display_name || `@${p.username}`}
                      </div>
                      <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400 truncate">
                        @{p.username} · {p.is_superuser ? "Superuser" : "Member"}
                      </div>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-cyan-700 dark:text-cyan-300 shrink-0">
                    {p.plan_name || "Starter"}
                  </span>
                </div>

                {p.bio && (
                  <p className="text-[11px] text-slate-600 dark:text-slate-400 line-clamp-2">{p.bio}</p>
                )}

                <div className="flex flex-wrap items-center justify-between gap-1.5 text-[10px] font-mono text-slate-500 dark:text-slate-400 pt-1 border-t border-slate-200/70 dark:border-slate-800/70">
                  <span className="flex items-center gap-1 truncate">
                    <Mail className="w-3 h-3" />
                    {p.email || "no-email"}
                  </span>
                  <span className="flex items-center gap-1">
                    {p.organization && (
                      <>
                        <Building2 className="w-3 h-3" />
                        {p.organization} ·
                      </>
                    )}
                    <Sparkles className="w-3 h-3 text-indigo-500" />
                    {(p.default_tier || "flash").toUpperCase()}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

