module.exports = {
  plugins: {
    '@tailwindcss/postcss': {},
    'postcss-preset-env': {
      features: {
        'oklab-function': { preserve: false },
      },
    },
    autoprefixer: {},
  },
};