import { Navigate, Route, Routes } from 'react-router-dom';
import ChatPage from './pages/ChatPage';
import SharedConversationPage from './pages/SharedConversationPage';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ChatPage />} />
      <Route path="/share/:conversationId" element={<SharedConversationPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
