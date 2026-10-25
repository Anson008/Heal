function SaplingLoader() {
  return (
    <div className="sapling-loader" role="status" aria-label="Loading">
      <svg
        viewBox="0 0 100 100"
        width="48"
        height="48"
        className="sapling-svg"
      >
        <ellipse cx="50" cy="92" rx="28" ry="5" fill="#8b5e3c" opacity="0.5" />
        <line x1="50" y1="90" x2="50" y2="50" className="sapling-stem" />
        <g className="sapling-leaf sapling-leaf-left">
          <path d="M50,70 C35,68 30,58 32,50 C42,52 50,60 50,70 Z" />
        </g>
        <g className="sapling-leaf sapling-leaf-right">
          <path d="M50,58 C65,56 70,46 68,38 C58,40 50,48 50,58 Z" />
        </g>
        <g className="sapling-leaf sapling-leaf-top">
          <path d="M50,50 C41,47 36,38 38,29 C48,32 54,42 50,50 Z" />
        </g>
      </svg>
    </div>
  );
}

export default SaplingLoader;