import React from "react";

function ToggleSwitch({ label, enabled, setEnabled, disabled = false }) {
    return (
        <div className="flex items-center space-x-3">
            <span className={`text-sm ${disabled ? "text-gray-400" : "text-gray-800"}`}>{label}</span>
            <button
                onClick={() => !disabled && setEnabled(!enabled)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                    enabled ? "bg-indigo-600" : "bg-gray-300"
                } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
            >
                <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                        enabled ? "translate-x-6" : "translate-x-1"
                    }`}
                />
            </button>
        </div>
    );
}

export default ToggleSwitch;