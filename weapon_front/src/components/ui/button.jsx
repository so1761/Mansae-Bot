import React from "react";

export function Button({ children, className = "", ...props }) {
  return (
    <button
      className={`rounded px-4 py-2 font-medium bg-blue-600 text-white hover:bg-blue-700 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
