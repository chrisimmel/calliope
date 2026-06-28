/**
 * Three-ring loader (spec §6.10). `page` = 64px centered loader for full-view
 * loading; `inline` = 32px for the corner generation spinner.
 */

import React from 'react';

import './Loader.css';

export default function Loader({
  size = 'page',
}: {
  size?: 'page' | 'inline';
}) {
  return (
    <div
      className={`loader loader--${size}`}
      role="status"
      aria-label="Loading"
    >
      <div className="inner one"></div>
      <div className="inner two"></div>
      <div className="inner three"></div>
    </div>
  );
}
