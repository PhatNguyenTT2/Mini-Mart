import { Header } from "../components/Header";
import HomeMerchandising from "../components/HomeMerchandising/HomeMerchandising";
import Footer from "../components/Footer/Footer";

export default function Home() {
  return (
    <>
      <Header />
      <main className="max-w-[1440px] mx-auto px-4 lg:px-8 py-8">
        <HomeMerchandising />
      </main>
      <Footer />
    </>
  );
}
