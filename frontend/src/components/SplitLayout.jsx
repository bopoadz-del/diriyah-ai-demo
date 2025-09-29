import React, { useCallback, useState } from "react";
import Analytics from "./Analytics";
import ChatWindow from "./ChatWindow";

const MIN_WIDTH_PERCENT = 20;
const MAX_WIDTH_PERCENT = 80;

const SplitLayout = () => {
  const [dividerPosition, setDividerPosition] = useState(50);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = () => { setIsDragging(true); };
  const handleMouseUp = () => { setIsDragging(false); };

  const handleMouseMove = useCallback((event) => {
    if (!isDragging) return;
    const nextPosition = (event.clientX / window.innerWidth) * 100;
    if (nextPosition > MIN_WIDTH_PERCENT && nextPosition < MAX_WIDTH_PERCENT) setDividerPosition(nextPosition);
  }, [isDragging]);

  return (
    <div className="split-layout" onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
      <div className="left-panel" style={{ width: `${dividerPosition}%` }}><ChatWindow /></div>
      <div className="divider" role="separator" aria-orientation="vertical" tabIndex={0} onMouseDown={handleMouseDown} />
      <div className="right-panel" style={{ width: `${100 - dividerPosition}%` }}><Analytics /></div>
    </div>
  );
};
export default SplitLayout;
