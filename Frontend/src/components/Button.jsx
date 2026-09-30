import './Button.css'

// The app's button. tone: neutral | info | success | danger | warning |
// accent. appearance: tinted (default) | outline | ghost | solid (one main
// action per screen). size: sm 30px | md 36px | lg 44px (44px on touch).
// shape: pill | rect. `selected` marks a toggle, filter or open panel.
// Layout (width, grid placement) stays the caller's, via className/style.
export function Button({
  tone = 'neutral',
  appearance = 'tinted',
  size = 'md',
  shape = 'pill',
  selected = false,
  block = false,
  align = 'center',
  icon = false,
  className = '',
  type = 'button',
  children,
  ...props
}) {
  const classes = [
    'btn', `btn--${tone}`, `btn--${appearance}`, `btn--${size}`,
    shape === 'rect' ? 'btn--rect' : '',
    block ? 'btn--block' : '',
    align === 'start' ? 'btn--start' : '',
    icon ? 'btn--icon' : '',
    selected ? 'is-selected' : '',
    className,
  ].filter(Boolean).join(' ')
  return (
    <button type={type} className={classes} aria-pressed={selected ? true : undefined} {...props}>
      {children}
    </button>
  )
}

// A row in a menu or dropdown list. tone colours the text only.
export function MenuItem({ tone = 'neutral', selected = false, className = '', type = 'button', children, ...props }) {
  const classes = ['menu-item', tone !== 'neutral' ? `menu-item--${tone}` : '', selected ? 'is-selected' : '', className].filter(Boolean).join(' ')
  return (
    <button type={type} className={classes} {...props}>
      {children}
    </button>
  )
}

export default Button
