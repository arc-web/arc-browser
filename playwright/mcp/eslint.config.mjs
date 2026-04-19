import tseslint from '@typescript-eslint/eslint-plugin';
import parser from '@typescript-eslint/parser';

export default [
    {
        files: ['src/**/*.ts', 'src/**/*.js'],
        languageOptions: {
            parser,
            parserOptions: {
                project: './tsconfig.json',
                sourceType: 'module',
            },
            globals: {
                node: true,
                es2021: true,
            },
        },
        plugins: {
            '@typescript-eslint': tseslint,
        },
        rules: {
            '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
        },
    },
];
