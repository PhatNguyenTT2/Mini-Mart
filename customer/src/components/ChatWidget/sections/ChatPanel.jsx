import { ChatHeader } from './ChatHeader'
import { ChatMessages } from './ChatMessages'
import { ChatInput } from './ChatInput'

export const ChatPanel = () => {
  return (
    <div className="w-[380px] h-[520px] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden">
      <ChatHeader />
      <ChatMessages />
      <ChatInput />
    </div>
  )
}
