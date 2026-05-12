import { Bot, Search, Sparkles, Tag, HelpCircle } from 'lucide-react'

const suggestions = [
  { icon: Search,     label: 'Search products',     prompt: 'Tìm thịt bò nhập khẩu' },
  { icon: Sparkles,   label: 'Suggest for me',      prompt: 'Gợi ý sản phẩm phổ biến' },
  { icon: Tag,        label: 'Products on sale',    prompt: 'Sản phẩm đang giảm giá' },
  { icon: HelpCircle, label: 'Order guide',         prompt: 'Cách đặt hàng online' },
]

export const WelcomeScreen = ({ onSelectPrompt }) => {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4 py-6 select-none">
      {/* Bot avatar */}
      <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center mb-4 shadow-lg shadow-emerald-200">
        <Bot size={28} className="text-white" />
      </div>

      <h3 className="text-base font-semibold text-gray-800 mb-1">Shopping Assistant</h3>
      <p className="text-xs text-gray-400 mb-5 max-w-[220px] text-center leading-relaxed">
        Find products, compare prices, check sales — tap a suggestion or ask a question.
      </p>

      {/* Suggestion chips */}
      <div className="flex flex-wrap justify-center gap-2 max-w-[300px]">
        {suggestions.map((item, idx) => {
          const Icon = item.icon
          return (
            <button
              key={idx}
              onClick={() => onSelectPrompt(item.prompt)}
              className="group flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-gray-200 bg-white text-xs text-gray-600 hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-600 hover:scale-[1.03] hover:shadow-sm active:scale-[0.97] transition-all duration-150 cursor-pointer"
            >
              <Icon size={13} className="text-gray-400 group-hover:text-emerald-500 transition-colors" />
              <span>{item.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
