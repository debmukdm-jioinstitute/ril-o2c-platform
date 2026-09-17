// A neutral, abstract mark — deliberately not any real company's trademark. This platform is
// an independent research prototype, not an official internal tool of any organization; see
// README.md's data/branding disclaimers.
export default function Logo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="20" cy="20" r="19" fill="#16233f" />
      <path
        d="M20 8c4 4 6 8 6 12a6 6 0 1 1-12 0c0-4 2-8 6-12Z"
        fill="url(#logo-gradient)"
      />
      <defs>
        <linearGradient id="logo-gradient" x1="14" y1="8" x2="26" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#f3e2b0" />
          <stop offset="1" stopColor="#b8860f" />
        </linearGradient>
      </defs>
    </svg>
  );
}
