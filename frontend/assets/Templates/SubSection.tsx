import React from 'react';

export interface BulletItem {
  bullet_id?: string;
  text: string;
  bold_words?: string[];
}

export interface SkillItem {
  category: string;
  items: string;
}

interface SubSectionProps {
  title?: string;
  date?: string;
  role?: string;
  location?: string;
  bullets?: Array<string | BulletItem>;
  skills?: SkillItem[];
  children?: React.ReactNode;
}

export function SubSection({
  title,
  date,
  role,
  location,
  bullets,
  skills,
  children,
}: SubSectionProps) {
  // Helper to bold specific words in a text
  const highlightText = (text: string, boldWords?: string[]) => {
    if (!boldWords || boldWords.length === 0) return text;

    const escapedWords = boldWords
      .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      .filter(Boolean);

    if (escapedWords.length === 0) return text;

    const regex = new RegExp(`\\b(${escapedWords.join('|')})\\b`, 'gi');
    const parts = text.split(regex);

    return parts.map((part, index) => {
      const isMatch = boldWords.some(
        (w) => w.toLowerCase() === part.toLowerCase()
      );
      return isMatch ? <strong key={index}>{part}</strong> : part;
    });
  };

  const hasHeader = title || date || role || location;

  return (
    <div className="sub-section">
      {hasHeader && (
        <div className="sub-section-header">
          {title && <div className="sub-section-name">{title}</div>}
          {date && <div className="sub-section-date">{date}</div>}
          {role && <div className="sub-section-role">{role}</div>}
          {location && <div className="sub-section-location">{location}</div>}
        </div>
      )}

      {bullets && bullets.length > 0 && (
        <div className="sub-section-description">
          <ul>
            {bullets.map((bullet, index) => {
              if (typeof bullet === 'string') {
                return <li key={index}>{bullet}</li>;
              }
              return (
                <li key={bullet.bullet_id || index}>
                  {highlightText(bullet.text, bullet.bold_words)}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {skills && skills.length > 0 && (
        <div style={{ marginTop: '10px' }}>
          {skills.map((skill, index) => (
            <React.Fragment key={index}>
              <span className="skill-category sub-section-description">
                {skill.category}{' '}
              </span>
              <span className="skill-item sub-section-description">
                {skill.items}
              </span>
              {index < skills.length - 1 && <br />}
            </React.Fragment>
          ))}
        </div>
      )}

      {children}
    </div>
  );
}

export default SubSection;
