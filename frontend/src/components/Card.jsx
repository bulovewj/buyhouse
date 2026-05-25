export default function Card({ title, children, className = '' }) {
  return (
    <div className={`bg-gray-800 rounded-xl shadow-lg p-6 ${className}`}>
      {title && (
        <h2 className="text-lg font-bold text-white mb-4">{title}</h2>
      )}
      {children}
    </div>
  )
}
