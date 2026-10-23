import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        brand: {
          blue: "#0560DF",
          royal: "#0E2F9D",
          navy: "#17285E",
          orange: "#F94F0E",
          red: "#EE3128",
          magenta: "#D11753",
          surface: "#F8FAFC",
        },
        primary: {
          DEFAULT: "#0560DF",
          foreground: "#FFFFFF",
          hover: "#0E2F9D",
        },
        secondary: {
          DEFAULT: "#FFFFFF",
          foreground: "#17285E",
        },
        accent: {
          DEFAULT: "#F94F0E",
          foreground: "#FFFFFF",
        },
        destructive: {
          DEFAULT: "#EE3128",
          foreground: "#FFFFFF",
        },
        muted: {
          DEFAULT: "#F8FAFC",
          foreground: "#17285E",
        },
        card: {
          DEFAULT: "#FFFFFF",
          foreground: "#17285E",
        },
      },
      borderRadius: {
        lg: "8px",
        xl: "12px",
        "2xl": "16px",
        "3xl": "24px",
      },
      fontFamily: {
        sans: ["Inter", "Plus Jakarta Sans", "Manrope", "sans-serif"],
      },
      backgroundImage: {
        "cognitive-gradient": "linear-gradient(135deg, #0560DF 0%, #7A1FD0 50%, #EE3128 100%)",
        "motion-gradient": "linear-gradient(135deg, #0560DF 0%, #F94F0E 100%)",
      },
      boxShadow: {
        soft: "0 4px 20px -2px rgba(23, 40, 94, 0.06)",
        "soft-hover": "0 10px 30px -4px rgba(23, 40, 94, 0.12)",
        floating: "0 20px 40px -8px rgba(23, 40, 94, 0.16)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
