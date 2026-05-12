import React from "react";
import { HeaderSection } from "./sections/HeaderSection";
import { SearchBarSection } from "./sections/SearchBarSection";

export const Header = () => {
  return (
    <div className="flex flex-col items-center gap-[30px] relative">
      <SearchBarSection />
      <HeaderSection />
    </div>
  );
};
