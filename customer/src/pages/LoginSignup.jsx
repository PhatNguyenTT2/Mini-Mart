import { Header } from "../components/Header";
import Footer from "../components/Footer/Footer";
import { LoginSection } from "../components/LoginSignup";

export default function LoginSignup() {
  return (
    <>
      <Header />
      <div className="min-h-[60vh] bg-[#f4f6fa]">
        <LoginSection />
      </div>
      <Footer />
    </>
  );
}
