import { useId } from 'react'

/**
 * xPDFedit Logo Mark
 * 紅色漸層圓角方塊 + 白色 PDF 文件（折角） + 橘色鉛筆徽章
 */
export function LogoMark({ size = 40, className = '' }: { size?: number; className?: string }) {
  const uid = useId().replace(/:/g, '-')
  const gradId = `xpe-bg-${uid}`
  const shadowId = `xpe-sh-${uid}`

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="xPDFedit"
    >
      <defs>
        {/* 背景漸層：品牌紅 */}
        <linearGradient id={gradId} x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
          <stop stopColor="#E8152F" />
          <stop offset="1" stopColor="#8A0D22" />
        </linearGradient>
        {/* 文件陰影 */}
        <filter id={shadowId} x="-10%" y="-10%" width="120%" height="120%">
          <feDropShadow dx="0" dy="1" stdDeviation="1" floodOpacity="0.15" />
        </filter>
      </defs>

      {/* ── 背景 ── */}
      <rect width="40" height="40" rx="9" fill={`url(#${gradId})`} />

      {/* ── PDF 文件（白） ── */}
      <rect
        x="8" y="6" width="19" height="24"
        rx="2.5"
        fill="white" fillOpacity="0.97"
        filter={`url(#${shadowId})`}
      />

      {/* 折角三角（右上） */}
      <path d="M21 6 L27 12 L21 12 Z" fill="#C41230" fillOpacity="0.25" />
      {/* 折角邊線 */}
      <path d="M21 6 L27 12" stroke="#C41230" strokeOpacity="0.2" strokeWidth="0.5" />

      {/* 文件內容線條 */}
      <rect x="11" y="16" width="9"   height="1.8" rx="0.9" fill="#C41230" fillOpacity="0.38" />
      <rect x="11" y="19.5" width="12" height="1.8" rx="0.9" fill="#C41230" fillOpacity="0.38" />
      <rect x="11" y="23"  width="7.5" height="1.8" rx="0.9" fill="#C41230" fillOpacity="0.38" />

      {/* ── 編輯徽章（橘色圓） ── */}
      <circle cx="28.5" cy="28.5" r="10" fill="#FF6B2B" />
      {/* 徽章高光 */}
      <circle cx="26" cy="25.5" r="3.5" fill="white" fillOpacity="0.12" />

      {/* 鉛筆圖示（旋轉 -45°，尖端朝左下） */}
      <g transform="translate(28.5,28.5) rotate(-45)">
        {/* 橡皮擦端（半透明） */}
        <rect x="-1.9" y="-6.8" width="3.8" height="2.2" rx="0.8"
              fill="white" fillOpacity="0.55" />
        {/* 筆身 */}
        <rect x="-1.9" y="-4.6" width="3.8" height="7.5" rx="1" fill="white" />
        {/* 筆尖 */}
        <path d="M-1.9 2.9 L0 6.2 L1.9 2.9 Z" fill="white" fillOpacity="0.9" />
        {/* 筆尖分隔線 */}
        <line x1="-1.9" y1="2.9" x2="1.9" y2="2.9"
              stroke="#FF6B2B" strokeWidth="0.7" strokeOpacity="0.5" />
      </g>
    </svg>
  )
}
