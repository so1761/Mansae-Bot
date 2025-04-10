import React, { useState } from "react";
import { motion } from "framer-motion";

export default function Enhancement() {
  const [enhanceLevel, setEnhanceLevel] = useState(0);

  const enhancementChances = [
    100, 90, 90, 80, 80, 80, 70, 60, 60, 40,
    40, 30, 20, 20, 10, 10, 5, 5, 3, 1
  ];

  const handleEnhanceInput = (e) => {
    const level = parseInt(e.target.value);
    if (!isNaN(level) && level >= 0 && level < enhancementChances.length) {
      setEnhanceLevel(level);
    }
  };

  return (
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="bg-white shadow-xl rounded-2xl p-8 max-w-md w-full text-center"
      >
        <h1 className="text-3xl font-bold text-indigo-700 mb-6">🔨 강화 확률</h1>

        <div className="flex flex-col items-center mb-6">
          <label className="mb-2 text-gray-700 font-medium">
            강화 수치를 입력하세요
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="0"
              max="19"
              value={enhanceLevel}
              onChange={handleEnhanceInput}
              className="border border-gray-300 rounded-lg px-3 py-2 w-20 text-center focus:outline-none focus:ring-2 focus:ring-indigo-400 transition"
            />
            <span className="text-lg text-gray-600 font-semibold">강</span>
          </div>
        </div>

        <p className="text-xl font-semibold text-indigo-600">
          {enhanceLevel} → {enhanceLevel + 1}강:{" "}
          <span className="text-pink-600 font-bold">
            {enhancementChances[enhanceLevel]}%
          </span>{" "}
          성공 확률
        </p>
      </motion.div>
  );
}