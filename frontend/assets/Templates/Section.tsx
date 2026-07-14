import React from 'react';

interface SectionProps {
  title: string;
  children?: React.ReactNode;
}

export function Section({ title, children }: SectionProps) {
  return (
    <div className="section">
      <div className="section-name">{title}</div>
      {children}
    </div>
  );
}

export default Section;
