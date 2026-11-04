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
      'vue/multi-word-component-names': 'error',
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/first-attribute-linebreak': 'off',
      'vue/require-explicit-emits': 'error',
      'vue/component-api-style': ['error', ['script-setup']],
      'vue/block-order': ['error', { order: ['script', 'template', 'style'] }],
      'vue/define-props-declaration': ['error', 'type-based'],
      'vue/define-emits-declaration': ['error', 'type-based'],
      'vue/no-v-html': 'error',
      'vue/attributes-order': 'error',
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'no-console': ['error', { allow: ['warn', 'error'] }],
      'no-debugger': 'error',
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: 'axios',
              message: '网络请求统一经 src/api/client.ts',
            },
          ],
        },
      ],
      'no-restricted-globals': [
        'error',
        { name: 'fetch', message: '网络请求统一经 src/api/client.ts' },
        { name: 'XMLHttpRequest', message: '网络请求统一经 src/api/client.ts' },
        {
          name: 'localStorage',
          message: '认证/敏感信息不得放 Web Storage；确需使用请评审并 eslint-disable',
        },
        {
          name: 'sessionStorage',
          message: '认证/敏感信息不得放 Web Storage；确需使用请评审并 eslint-disable',
        },
      ],
    },
  },
  {
    files: ['src/api/client.ts'],
    rules: { 'no-restricted-imports': 'off' },
  },
]
