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
import DPA from "@/pages/DPA";
import MfaSetup from "@/pages/MfaSetup";
import Payouts from "@/pages/Payouts";
import Timetable from "@/pages/Timetable";
import Assessments from "@/pages/Assessments";
import Practice from "@/pages/Practice";
import Reports from "@/pages/Reports";
import Announcements from "@/pages/Announcements";
import Homework from "@/pages/Homework";
import ClassesRoster from "@/pages/ClassesRoster";
import VerifyDomain from "@/pages/VerifyDomain";

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
      <Route path="/dpa" element={<DPA />} />
      <Route path="/privacy" element={<DPA />} />
      <Route path="/mfa" element={<ProtectedRoute><MfaSetup /></ProtectedRoute>} />
      <Route path="/owner/payouts" element={<ProtectedRoute><Payouts /></ProtectedRoute>} />
      <Route path="/timetable" element={<ProtectedRoute><Timetable /></ProtectedRoute>} />
      <Route path="/homework" element={<ProtectedRoute><Homework /></ProtectedRoute>} />
      <Route path="/assessments" element={<ProtectedRoute><Assessments /></ProtectedRoute>} />
      <Route path="/practice" element={<ProtectedRoute><Practice /></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
      <Route path="/announcements" element={<ProtectedRoute><Announcements /></ProtectedRoute>} />
      <Route path="/classes" element={<ProtectedRoute><ClassesRoster /></ProtectedRoute>} />
      <Route path="/verify-domain" element={<VerifyDomain />} />
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
