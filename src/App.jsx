import { Navigate, Route, Routes } from 'react-router-dom';
import ChatPage from './pages/ChatPage';
import SkillPage from './pages/SkillPage';
import AdminPage from './pages/AdminPage';
import SharedConversationPage from './pages/SharedConversationPage';
import { SKILLS } from './skills';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ChatPage />} />
      {SKILLS.map((skill) => (
        <Route key={skill.mode} path={skill.path} element={<SkillPage skill={skill} />} />
      ))}
      <Route path="/admin" element={<AdminPage />} />
      <Route path="/share/:conversationId" element={<SharedConversationPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
