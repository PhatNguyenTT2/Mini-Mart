import { AboutSection } from './sections/AboutSection';
import { InformationSection } from './sections/InformationSection';

export default function Footer() {
  return (
    <footer className="bg-white border-t border-[#ececec] w-full">
      <div className="max-w-[1440px] mx-auto px-4 lg:px-8 py-12">
        <AboutSection />
      </div>
      <InformationSection />
    </footer>
  );
}
