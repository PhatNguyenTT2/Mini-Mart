import React from 'react'
import { Bot, Package, Search, ShoppingCart, Sparkles, HelpCircle } from 'lucide-react'

const suggestions = [
  { icon: Package,      label: 'Kiểm tra tồn kho',     prompt: 'Kiểm tra tồn kho sữa' },
  { icon: Search,       label: 'Tìm kiếm sản phẩm',    prompt: 'Tìm kiếm gia vị nấu ăn' },
  { icon: ShoppingCart,  label: 'Tra cứu đơn hàng',     prompt: 'Đơn hàng gần đây' },
  { icon: Sparkles,     label: 'Gợi ý sản phẩm',       prompt: 'Gợi ý sản phẩm bán chạy' },
  { icon: HelpCircle,   label: 'Hướng dẫn sử dụng',    prompt: 'Hướng dẫn sử dụng' },
]

export const WelcomeScreen = ({ onSelectPrompt }) => {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4 py-6 select-none">
      {/* Bot avatar */}
      <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center mb-4 shadow-lg shadow-blue-200">
        <Bot size={28} className="text-white" />
      </div>

      <h3 className="text-base font-semibold text-gray-800 mb-1">POSMART AI</h3>
      <p className="text-xs text-gray-400 mb-5 max-w-[220px] text-center leading-relaxed">
        Tìm sản phẩm, kiểm tra giá, tra cứu đơn hàng — chọn gợi ý hoặc gõ câu hỏi.
      </p>

      {/* Suggestion chips */}
      <div className="flex flex-wrap justify-center gap-2 max-w-[300px]">
        {suggestions.map((item, idx) => {
          const Icon = item.icon
          return (
            <button
              key={idx}
              onClick={() => onSelectPrompt(item.prompt)}
              className="group flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-gray-200 bg-white text-xs text-gray-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600 hover:scale-[1.03] hover:shadow-sm active:scale-[0.97] transition-all duration-150 cursor-pointer"
            >
              <Icon size={13} className="text-gray-400 group-hover:text-blue-500 transition-colors" />
              <span>{item.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
