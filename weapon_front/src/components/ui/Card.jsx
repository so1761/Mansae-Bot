export function Card({ children }) {
    return <div className="bg-white p-4 rounded-xl shadow">{children}</div>;
  }
  
  export function CardContent({ children }) {
    return <div className="mt-2">{children}</div>;
  }