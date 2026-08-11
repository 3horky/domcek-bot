export default {
  rules: {
    'color-no-hex': true,
  },
  overrides: [
    {
      files: ['src/styles/global.css'],
      rules: {
        // UX0 uzamyká presný existujúci dlh samostatnou kontrolou. Nové CSS súbory
        // už týmto pravidlom nesmú zaviesť priamu hex farbu.
        'color-no-hex': null,
      },
    },
  ],
}
