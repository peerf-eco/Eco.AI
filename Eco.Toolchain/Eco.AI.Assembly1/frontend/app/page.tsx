import { ChatInterface } from "@/components/chat/chat-interface";
import { SetupBanner } from "@/components/chat/setup-banner";

export default function Home() {
  return (
    <main className="h-screen flex flex-col">
      <SetupBanner />
      <div className="flex-1 min-h-0">
        <ChatInterface />
      </div>
    </main>
  );
}
