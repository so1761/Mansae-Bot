import React from "react";
import { motion } from "framer-motion";

export default function RandomBox() {
  return (
      <motion.div
        className="bg-white w-full max-w-4xl shadow-xl rounded-2xl p-10 sm:p-16"
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        <h1 className="text-3xl sm:text-4xl font-extrabold text-indigo-700 mb-6">
          🎁 랜덤박스 확률
        </h1>

        <ul className="text-left space-y-3 text-base sm:text-lg text-gray-800 font-medium">
          <li className="flex justify-between border-b pb-1">
            <span>강화재료 3개</span>
            <span className="text-indigo-600 font-semibold">20%</span>
          </li>
          <li className="flex justify-between border-b pb-1">
            <span>강화재료 5개</span>
            <span className="text-indigo-600 font-semibold">30%</span>
          </li>
          <li className="flex justify-between border-b pb-1">
            <span>강화재료 10개</span>
            <span className="text-indigo-600 font-semibold">10%</span>
          </li>
          <li className="flex justify-between border-b pb-1">
            <span>연마제 1개</span>
            <span className="text-indigo-600 font-semibold">15%</span>
          </li>
          
          <li className="flex justify-between border-b pb-1">
            <span>특수연마제 1개</span>
            <span className="text-amber-600 font-semibold">1%</span>
          </li>
          <li className="flex justify-between border-b pb-1">
            <span>레이드 재도전권 1개</span>
            <span className="text-indigo-600 font-semibold">20%</span>
          </li>
          <li className="flex justify-between">
            <span>꽝</span>
            <span className="text-red-500 font-semibold">4%</span>
          </li>
        </ul>
      </motion.div>
  );
}