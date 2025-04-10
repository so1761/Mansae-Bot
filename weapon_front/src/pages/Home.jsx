import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";

export default function Home() {
  return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="bg-white shadow-2xl rounded-2xl p-10 max-w-xl w-full text-center"
      >
        <h1 className="text-4xl font-extrabold text-indigo-700 mb-4">⚔️ 무기 시뮬레이터</h1>
        <p className="text-lg text-gray-700 mb-6">
          강화 확률, 무기 정보, 계승 시스템까지!
          <br />
          무기 시스템을 손쉽게 시뮬레이션하고 관리하세요.
        </p>
        <div className="flex flex-col sm:flex-row justify-center gap-4">
        <Link
          to="/probability/randombox"
          className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-6 rounded-lg transition"
        >
          랜덤박스 보기
        </Link>
        <Link
          to="/weapon"
          className="bg-purple-600 hover:bg-purple-700 text-white font-semibold py-2 px-6 rounded-lg transition"
        >
          무기 정보
        </Link>
        </div>
      </motion.div>
  );
}