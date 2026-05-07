"use client";

import * as React from "react";

type Theme = "light" | "dark";

type ThemeContextValue = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggle: () => void;
};

const ThemeContext = React.createContext<ThemeContextValue | null>(null);

const STORAGE_KEY = "mna-ui-theme";

function readInitialTheme(): Theme {
  if (typeof document === "undefined") return "light";
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>(readInitialTheme);

  const setTheme = React.useCallback((next: Theme) => {
    setThemeState(next);
    if (typeof document !== "undefined") {
      document.documentElement.classList.toggle("dark", next === "dark");
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        /* ignore storage errors */
      }
    }
  }, []);

  const toggle = React.useCallback(() => {
    setTheme(theme === "dark" ? "light" : "dark");
  }, [theme, setTheme]);

  // Sync state with documentElement class on mount in case the inline script set it.
  React.useEffect(() => {
    setThemeState(readInitialTheme());
  }, []);

  const value = React.useMemo(() => ({ theme, setTheme, toggle }), [theme, setTheme, toggle]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = React.useContext(ThemeContext);
  if (!ctx) {
    return {
      theme: "light",
      setTheme: () => {},
      toggle: () => {},
    };
  }
  return ctx;
}

/** Inline script content for the document head — sets the .dark class before paint to avoid FOUC. */
export const themeScript = `(function(){try{var k='${STORAGE_KEY}';var s=localStorage.getItem(k);var p=window.matchMedia('(prefers-color-scheme: dark)').matches;var t=s||(p?'dark':'light');if(t==='dark')document.documentElement.classList.add('dark');}catch(e){}})();`;
