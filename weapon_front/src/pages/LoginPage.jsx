import React from "react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { LogIn } from "lucide-react";

export default function LoginPage() {
const handleLogin = () => {
    const handleLogin = () => {
  window.location.href =
    "https://discord.com/oauth2/authorize?client_id=1359041889936080896&response_type=code&redirect_uri=http%3A%2F%2F35.233.128.144%3A3000%2Foauth%2F&scope=identify+email";
};

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-100 to-white">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="bg-white p-10 rounded-2xl shadow-xl text-center max-w-md w-full"
      >
        <h1 className="text-3xl sm:text-4xl font-extrabold text-indigo-700 mb-4">무기 정보 시스템</h1>
        <p className="text-gray-600 text-sm mb-6">
          Discord로 로그인하여 나의 무기 스탯을 확인하세요.
        </p>

        <Button
          onClick={handleLogin}
          className="w-full flex items-center justify-center gap-2 text-lg font-semibold bg-indigo-600 hover:bg-indigo-700 text-white py-3 px-6 rounded-xl shadow-md"
        >
          <LogIn className="w-5 h-5" /> Discord로 로그인
        </Button>
      </motion.div>
    </div>
  );
}
