"use client";

import React from "react";

export function DotBorderWrapper({ 
  children, 
  className = "" 
}: { 
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div 
      className={`relative inline-flex group ${className}`} 
      style={{
        '--dot-size': '4px',
        '--line-weight': '1px',
        '--animation-speed': '0.35s',
        '--dot-color': 'rgba(255, 255, 255, 0.6)',
        '--line-color': 'rgba(255, 255, 255, 0.3)',
        '--grid-color': 'rgba(255, 255, 255, 0.05)'
      } as React.CSSProperties}
    >
      <style>{`
         .animated-wrapper::after {
            content: "";
            position: absolute;
            inset: 0;
            background-image: repeating-linear-gradient(45deg, var(--grid-color) 0 1px, transparent 2px 5px);
            opacity: 0;
            z-index: 0;
            border-radius: inherit;
            transition: opacity calc(var(--animation-speed) * 2) ease-in-out;
         }
         
         .group:hover .animated-wrapper::after {
            opacity: 1;
         }
         
         .anim-line {
            position: absolute;
            background-color: var(--line-color);
            z-index: 1;
            transition: transform var(--animation-speed) ease-in-out;
         }
         
         .anim-line.horizontal { width: 100%; height: var(--line-weight); transform: scaleX(0); }
         .anim-line.vertical { height: 100%; width: var(--line-weight); transform: scaleY(0); }

         .anim-line.top { top: 0; left: 0; transform-origin: left; }
         .anim-line.bottom { bottom: 0; right: 0; transform-origin: right; }
         .anim-line.left { bottom: 0; left: 0; transform-origin: bottom; }
         .anim-line.right { top: 0; right: 0; transform-origin: top; }

         .group:hover .anim-line { transform: scaleX(1) scaleY(1); }

         .anim-dot {
            position: absolute;
            width: var(--dot-size);
            height: var(--dot-size);
            background-color: var(--dot-color);
            border-radius: 50%;
            opacity: 0;
            z-index: 2;
            transition: all var(--animation-speed) ease-in-out;
         }
         
         .anim-dot.top-left { top: -2px; left: -2px; transform: translate(10px, 10px); }
         .anim-dot.top-right { top: -2px; right: -2px; transform: translate(-10px, 10px); }
         .anim-dot.bottom-left { bottom: -2px; left: -2px; transform: translate(10px, -10px); }
         .anim-dot.bottom-right { bottom: -2px; right: -2px; transform: translate(-10px, -10px); }

         .group:hover .anim-dot {
            transform: translate(0, 0);
            opacity: 1;
         }
         
         .group:hover .anim-dot.top-left { transition-delay: 0s; }
         .group:hover .anim-dot.top-right { transition-delay: 0.1s; }
         .group:hover .anim-dot.bottom-right { transition-delay: 0.2s; }
         .group:hover .anim-dot.bottom-left { transition-delay: 0.3s; }
      `}</style>
      
      {/* Decorative Border Elements */}
      <div className="animated-wrapper absolute inset-0 rounded-lg pointer-events-none">
         <div className="anim-line horizontal top rounded-t-lg"></div>
         <div className="anim-line vertical right rounded-r-lg"></div>
         <div className="anim-line horizontal bottom rounded-b-lg"></div>
         <div className="anim-line vertical left rounded-l-lg"></div>

         <div className="anim-dot top-left"></div>
         <div className="anim-dot top-right"></div>
         <div className="anim-dot bottom-right"></div>
         <div className="anim-dot bottom-left"></div>
      </div>
      
      {/* User's Original Button/Link Content */}
      <div className="relative z-10 w-full h-full flex">
        {children}
      </div>
    </div>
  );
}

export default DotBorderWrapper;
