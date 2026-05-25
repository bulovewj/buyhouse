const variantMap = {
  default: 'bg-gray-600 text-gray-100',
  success: 'bg-green-700 text-green-100',
  warning: 'bg-yellow-600 text-yellow-100',
  danger: 'bg-red-700 text-red-100',
  info: 'bg-blue-700 text-blue-100',
}

export default function Badge({ text, variant = 'default' }) {
  const cls = variantMap[variant] ?? variantMap.default
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      {text}
    </span>
  )
}
