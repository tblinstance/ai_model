import React, { useState, useEffect } from "react";

interface UserAvatarProps {
  avatar?: string;
  name?: string;
  className?: string;
  sizeClass?: string;
  roundedClass?: string;
  textSizeClass?: string;
}

export const UserAvatar: React.FC<UserAvatarProps> = ({
  avatar,
  name,
  className = "",
  sizeClass = "w-8 h-8",
  roundedClass = "rounded-full",
  textSizeClass = "text-xs",
}) => {
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    setLoadError(false);
  }, [avatar]);

  const initials = (name || "U").trim().slice(0, 2).toUpperCase() || "U";

  if (avatar && !loadError) {
    return (
      <img
        src={avatar}
        alt={name || "Avatar"}
        onError={() => setLoadError(true)}
        className={`${sizeClass} ${roundedClass} object-cover shrink-0 shadow-xs ring-1 ring-cyan-500/30 transition ${className}`}
      />
    );
  }

  return (
    <div
      className={`${sizeClass} ${roundedClass} bg-gradient-to-tr from-indigo-500 via-cyan-500 to-purple-600 text-white font-display font-bold ${textSizeClass} flex items-center justify-center shrink-0 shadow-xs select-none transition ${className}`}
    >
      {initials}
    </div>
  );
};

