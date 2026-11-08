// Type scale (desktop, root 16px→ html 100%): body 14, subtitle 20, title 28.
// On small screens typography.css lowers the root size so everything shrinks proportionally.
tailwind.config = {
  theme: {
    extend: {
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1rem' }],
        sm: ['0.8125rem', { lineHeight: '1.25rem' }],
        base: ['0.875rem', { lineHeight: '1.5rem' }],
        lg: ['1rem', { lineHeight: '1.5rem' }],
        xl: ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.75rem', { lineHeight: '2.25rem' }],
      },
    },
  },
};
