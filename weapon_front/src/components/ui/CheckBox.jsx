import React from "react";

function CheckBox({ label, checked, onChange, disabled = false }) {
    return (
        <label className="inline-flex items-center space-x-2 cursor-pointer select-none">
            <input
                type="checkbox"
                className="form-checkbox h-5 w-5 text-indigo-600 rounded transition"
                checked={checked}
                onChange={onChange}
                disabled={disabled}
            />
            <span className={`text-sm ${disabled ? "text-gray-400" : "text-gray-800"}`}>{label}</span>
        </label>
    );
}

export default CheckBox;