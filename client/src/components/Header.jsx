import React from "react";
import Logo from "../assets/YAML2Diagram-Logo.svg?react";
import { SiGithub } from "react-icons/si";
import { MdLightMode, MdDarkMode } from "react-icons/md";
import "./Header.css";

const Header = () => {
  return (
    <div id="header">
      <Logo className="logo w-80" />
      <div className="flex h-full max-h-full p-1 space-x-11 items-center">
        <a
          href="https://github.com/MarioAlexis/YAML2Diagram"
          className="header-icon"
          target="_blank"
        >
          <SiGithub className="header-icon"/>
        </a>
        <MdDarkMode className="header-icon" />
      </div>
    </div>
  );
};

export default Header;
