/**
 * Vue 3 CDN Profile & Workspace Directory component.
 */
window.ProfilePanelComponent = {
  props: ["store", "onUpdateProfile"],
  template: `
    <section class="space-y-4">
      <!-- Compact Profile Overview Banner (sm) -->
      <div class="glass-panel rounded-xl p-4 flex flex-wrap items-center justify-between gap-3">
        <input
          ref="avatarInput"
          type="file"
          accept="image/*"
          @change="handleAvatarUpload"
          class="hidden"
        />
        <div class="flex items-center gap-3">
          <div class="relative group shrink-0">
            <img
              v-if="form.avatar"
              :src="form.avatar"
              :alt="store.user?.username || 'Avatar'"
              class="w-12 h-12 rounded-xl object-cover ring-2 ring-indigo-500/40 shadow-xs"
            />
            <div v-else class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 via-cyan-500 to-purple-600 text-white font-display font-bold text-sm flex items-center justify-center shrink-0 shadow-xs">
              {{ (store.user?.display_name || store.user?.username || 'U').slice(0, 2).toUpperCase() }}
            </div>
            <button
              type="button"
              @click="$refs.avatarInput?.click()"
              title="Click to change profile avatar"
              class="absolute inset-0 rounded-xl bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center text-white transition-opacity cursor-pointer"
            >
              <i data-lucide="camera" class="w-4 h-4"></i>
            </button>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h2 class="font-display font-bold text-base text-slate-900 dark:text-white">
                {{ store.user?.display_name || ('@' + (store.user?.username || 'user')) }}
              </h2>
              <span class="px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-mono text-[10px]">
                {{ store.user?.is_superuser ? 'Superuser' : (store.user?.is_staff ? 'Staff' : 'Member') }}
              </span>
            </div>
            <div class="text-xs font-mono text-slate-500 dark:text-slate-400">
              @{{ store.user?.username }} · {{ store.user?.role_title || 'AI Builder' }}
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-xs font-mono">
          <span class="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-cyan-700 dark:text-cyan-300">
            {{ store.user?.plan_name || store.subscription?.plan?.name || 'Free' }}
          </span>
          <span class="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200">
            {{ formatCreditsBdtUsd(store.user?.remaining_credits ?? store.quota?.remaining_credits ?? 0) }}
          </span>
        </div>
      </div>

      <!-- Editable Profile Form -->
      <form @submit.prevent="submitProfile" class="glass-panel rounded-xl p-4 space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
            <i data-lucide="user-check" class="w-4 h-4 text-cyan-600 dark:text-cyan-400"></i>
            <span>Profile &amp; Preferences</span>
          </h3>
          <button
            type="submit"
            class="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5"
          >
            <i data-lucide="check" class="w-3.5 h-3.5"></i>
            <span>Save Profile</span>
          </button>
        </div>

        <!-- Avatar Management Card -->
        <div class="rounded-xl p-3 bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="relative shrink-0">
              <img
                v-if="form.avatar"
                :src="form.avatar"
                :alt="store.user?.username || 'Avatar'"
                class="w-12 h-12 rounded-xl object-cover ring-2 ring-indigo-500/40 shadow-xs"
              />
              <div v-else class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 via-cyan-500 to-purple-600 text-white font-display font-bold text-sm flex items-center justify-center shrink-0 shadow-xs">
                {{ (store.user?.display_name || store.user?.username || 'U').slice(0, 2).toUpperCase() }}
              </div>
            </div>
            <div>
              <div class="text-xs font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                <i data-lucide="camera" class="w-3.5 h-3.5 text-indigo-500"></i>
                <span>Profile Avatar</span>
              </div>
              <p class="text-[11px] text-slate-500 dark:text-slate-400">
                Upload a custom photo or avatar image (PNG, JPG, WebP, GIF, up to 5MB).
              </p>
              <p v-if="avatarError" class="text-[11px] text-rose-500 mt-0.5">{{ avatarError }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button
              type="button"
              @click="$refs.avatarInput?.click()"
              class="px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-500/15 hover:bg-indigo-100 dark:hover:bg-indigo-500/25 text-indigo-700 dark:text-indigo-300 text-xs font-semibold flex items-center gap-1.5 border border-indigo-200 dark:border-indigo-500/30 transition cursor-pointer"
            >
              <i data-lucide="upload" class="w-3.5 h-3.5"></i>
              <span>{{ form.avatar ? 'Change Avatar' : 'Upload Avatar' }}</span>
            </button>
            <button
              v-if="form.avatar"
              type="button"
              @click="handleRemoveAvatar"
              class="px-2.5 py-1.5 rounded-lg bg-rose-50 dark:bg-rose-500/10 hover:bg-rose-100 dark:hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 text-xs font-semibold flex items-center gap-1 border border-rose-200 dark:border-rose-500/20 transition cursor-pointer"
              title="Remove custom avatar and use initials"
            >
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
              <span>Remove</span>
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <div>
            <label class="block text-[11px] font-mono text-slate-500 mb-1">Display Name</label>
            <input v-model="form.display_name" type="text" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100" />
          </div>
          <div>
            <label class="block text-[11px] font-mono text-slate-500 mb-1">Email</label>
            <input v-model="form.email" type="email" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100" />
          </div>
          <div>
            <label class="block text-[11px] font-mono text-slate-500 mb-1">Role Title</label>
            <input v-model="form.role_title" type="text" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100" />
          </div>
          <div>
            <label class="block text-[11px] font-mono text-slate-500 mb-1">Organization</label>
            <input v-model="form.organization" type="text" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100" />
          </div>
          <div>
            <label class="block text-[11px] font-mono text-slate-500 mb-1">Default Tier</label>
            <select v-model="form.default_tier" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100">
              <option value="flash">tblinc Flash</option>
              <option value="pro">tblinc Pro</option>
              <option value="advance">tblinc Advance</option>
            </select>
          </div>
          <div>
            <label class="block text-[11px] font-mono text-slate-500 mb-1">Default Mode</label>
            <select v-model="form.default_task" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100">
              <option value="chat">AI Chat</option>
              <option value="images">Create Images</option>
              <option value="video">Create Videos</option>
              <option value="code">Create Code</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-[11px] font-mono text-slate-500 mb-1">Bio</label>
          <textarea v-model="form.bio" rows="2" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-2.5 text-xs text-slate-900 dark:text-slate-100"></textarea>
        </div>
      </form>

      <!-- Workspace Profiles List (compact sm cards) -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <div
          v-for="p in store.profiles"
          :key="'prof-' + p.id"
          class="glass-panel rounded-xl p-3.5 space-y-1.5"
          :class="p.id === store.user?.id ? 'border-cyan-500/50' : ''"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="font-display font-semibold text-xs text-slate-900 dark:text-white truncate">
              {{ p.display_name || ('@' + p.username) }}
            </span>
            <span class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-[10px] text-cyan-700 dark:text-cyan-300">
              {{ p.plan_name || 'Starter' }}
            </span>
          </div>
          <div class="text-[11px] font-mono text-slate-500 dark:text-slate-400 truncate">
            @{{ p.username }} · {{ p.email || 'no-email' }}
          </div>
          <p v-if="p.bio" class="text-[11px] text-slate-600 dark:text-slate-400 line-clamp-2">{{ p.bio }}</p>
        </div>
      </div>
    </section>
  `,
  setup(props) {
    const { reactive, ref, watch } = Vue;
    const avatarError = ref("");
    const form = reactive({
      display_name: props.store.user?.display_name || "",
      avatar: props.store.user?.avatar || "",
      email: props.store.user?.email || "",
      role_title: props.store.user?.role_title || "AI Builder",
      organization: props.store.user?.organization || "",
      default_tier: props.store.user?.default_tier || "flash",
      default_task: props.store.user?.default_task || "chat",
      bio: props.store.user?.bio || "",
    });
    watch(
      () => props.store.user,
      (u) => {
        if (!u) return;
        form.display_name = u.display_name || "";
        form.avatar = u.avatar || "";
        form.email = u.email || "";
        form.role_title = u.role_title || "AI Builder";
        form.organization = u.organization || "";
        form.default_tier = u.default_tier || "flash";
        form.default_task = u.default_task || "chat";
        form.bio = u.bio || "";
      },
      { deep: true }
    );
    const handleAvatarUpload = (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      avatarError.value = "";
      if (!file.type.startsWith("image/")) {
        avatarError.value = "Please select a valid image file.";
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        avatarError.value = "Avatar image must be under 5 MB.";
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const rawUrl = reader.result;
        form.avatar = rawUrl;
        if (props.onUpdateProfile) {
          props.onUpdateProfile({ avatar: rawUrl });
        }
      };
      reader.onerror = () => {
        avatarError.value = "Failed to read image file.";
      };
      reader.readAsDataURL(file);
    };
    const handleRemoveAvatar = () => {
      form.avatar = "";
      avatarError.value = "";
      if (props.onUpdateProfile) {
        props.onUpdateProfile({ avatar: "" });
      }
    };
    const submitProfile = () => {
      if (props.onUpdateProfile) {
        props.onUpdateProfile({ ...form });
      }
    };
    const formatCreditsBdtUsd = (c, opts) => window.AIModelBilling.formatCreditsBdtUsd(c, opts);
    return {
      avatarError,
      form,
      handleAvatarUpload,
      handleRemoveAvatar,
      submitProfile,
      formatCreditsBdtUsd,
    };
  },
};

