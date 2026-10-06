/** Shield-shaped "Y" crest used for the logo and the chat avatar (inline SVG, no image files). */
export default function YaleMark({ size = 44, title = 'Campus Customs' }: { size?: number; title?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label={title} className="yale-mark">
      <path d="M6 4h52v40L32 60 6 44z" fill="#00356b" />
      <path d="M10 8h44v34.5L32 55.5 10 42.5z" fill="none" stroke="#fff" strokeWidth="1.5" opacity="0.55" />
      <path d="M6 4h52v5H6z" fill="#a51c30" />
      <text x="32" y="41" fontFamily="'Libre Caslon Text', Georgia, serif" fontSize="30" fontWeight="700" fill="#fff" textAnchor="middle">
        Y
      </text>
    </svg>
  )
}
