import React from "react";
import { motion } from "framer-motion";

export default function Inheritance() {
  return (
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="bg-white shadow-xl rounded-2xl p-8 max-w-md w-full text-center"
      >
        <h1 className="text-3xl font-extrabold text-indigo-700 mb-6">
          🧬 계승 확률
        </h1>
        <ul className="list-disc pl-6 space-y-3 text-left text-lg text-gray-700">
          <li>
            <span className="font-semibold text-indigo-600">70%</span> 확률: 기본 스탯 증가
          </li>
          <li>
            <span className="font-semibold text-pink-600">30%</span> 확률: 기본 스킬 레벨 증가
          </li>
        </ul>
      </motion.div>
  );
}