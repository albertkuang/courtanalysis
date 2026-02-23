/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                tennis: {
                    dark: '#0f172a',
                    card: '#1e293b',
                    green: '#84cc16',
                    blue: '#0ea5e9',
                }
            }
        },
    },
    plugins: [],
}
