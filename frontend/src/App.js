import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import "@/App.css";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import { Toaster } from "@/components/ui/sonner";
import { applyA11yOnLoad } from "@/components/AccessibilityMenu";

applyA11yOnLoad();

import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import SchoolSignup from "@/pages/SchoolSignup";
import AuthCallback from "@/pages/AuthCallback";
import Dashboard from "@/pages/Dashboard";
import Subjects from "@/pages/Subjects";
import Topic from "@/pages/Topic";
import Focus from "@/pages/Focus";
import Progress from "@/pages/Progress";
import Pricing from "@/pages/Pricing";
import BillingSuccess from "@/pages/BillingSuccess";
import Help from "@/pages/Help";
import Owner from "@/pages/Owner";
import Teacher from "@/pages/Teacher";
import MyRecord from "@/pages/MyRecord";
import Dreams from "@/pages/Dreams";
import Suggestions from "@/pages/Suggestions";
import Safety from "@/pages/Safety";
import Contact from "@/pages/Contact";
import MfaSetup from "@/pages/MfaSetup";
import Payouts from "@/pages/Payouts";

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/signup/school" element={<SchoolSignup />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/subjects" element={<ProtectedRoute><Subjects /></ProtectedRoute>} />
      <Route path="/subjects/:subjectId" element={<ProtectedRoute><Subjects /></ProtectedRoute>} />
      <Route path="/subjects/:subjectId/topic/:topicId" element={<ProtectedRoute><Topic /></ProtectedRoute>} />
      <Route path="/focus" element={<ProtectedRoute><Focus /></ProtectedRoute>} />
      <Route path="/progress" element={<ProtectedRoute><Progress /></ProtectedRoute>} />
      <Route path="/pricing" element={<Pricing />} />
      <Route path="/billing/success" element={<ProtectedRoute><BillingSuccess /></ProtectedRoute>} />
      <Route path="/help" element={<ProtectedRoute><Help /></ProtectedRoute>} />
      <Route path="/owner" element={<ProtectedRoute><Owner /></ProtectedRoute>} />
      <Route path="/teacher" element={<ProtectedRoute><Teacher /></ProtectedRoute>} />
      <Route path="/my-record" element={<ProtectedRoute><MyRecord /></ProtectedRoute>} />
      <Route path="/dreams" element={<ProtectedRoute><Dreams /></ProtectedRoute>} />
      <Route path="/suggestions" element={<ProtectedRoute><Suggestions /></ProtectedRoute>} />
      <Route path="/safety" element={<Safety />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/mfa" element={<ProtectedRoute><MfaSetup /></ProtectedRoute>} />
      <Route path="/owner/payouts" element={<ProtectedRoute><Payouts /></ProtectedRoute>} />
      <Route path="*" element={<Landing />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster position="top-right" richColors />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
