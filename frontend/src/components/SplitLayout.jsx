import React, { useState, useRef } from "react";
import ChatWindow from "./ChatWindow";
import Analytics from "./Analytics";
const SplitLayout = () => {
  const [dividerPos, setDividerPos] = useState(50);
  const isDragging = useRef(false);
  const startDrag = () => { isDragging.current = true; };
  const stopDrag = () => { isDragging.current = false; };
  const onDrag = (e) => { if (!isDragging.current) return; const newPos = (e.clientX / window.innerWidth) * 100; if (newPos > 20 && newPos < 80) setDividerPos(newPos); };
  return (
    <div className="split-layout" onMouseMove={onDrag} onMouseUp={stopDrag} onMouseLeave={stopDrag}>
      <div className="left-panel" style={{ width: `${dividerPos}%` }}><ChatWindow /></div>
      <div className="divider" onMouseDown={startDrag} />
      <div className="right-panel" style={{ width: `${100 - dividerPos}%` }}><Analytics /></div>
    </div>
  );
};
export default SplitLayout;
