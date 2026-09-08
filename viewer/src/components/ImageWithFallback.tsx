import { useState } from 'react';

interface ImageWithFallbackProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  fallbackText: string;
  className?: string;
  style?: React.CSSProperties;
}

export default function ImageWithFallback({ src, fallbackText, className, style, ...props }: ImageWithFallbackProps) {
  const [error, setError] = useState(false);

  if (!src || error) {
    return (
      <div className={`fallback-img ${className || ''}`} style={style}>
        {fallbackText}
      </div>
    );
  }

  return (
    <img 
      src={src} 
      className={className} 
      style={style} 
      onError={() => setError(true)} 
      {...props} 
    />
  );
}
