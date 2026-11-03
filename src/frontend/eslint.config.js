import vue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'

const tsConfigs = tseslint.configs.recommended.map((config) => ({
  ...config,
  files: ['**/*.ts'],
}))

export default [
  { ignores: ['dist/**', 'node_modules/**', 'coverage/**', 'scripts/screenshots.mjs'] },
  ...vue.configs['flat/recommended'],
  ...tsConfigs,
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
        extraFileExtensions: ['.vue'],
      },
    },
  },
  {
    files: ['**/*.{ts,vue}'],
    plugins: { '@typescript-eslint': tseslint.plugin },
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/first-attribute-linebreak': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    },
  },
]
