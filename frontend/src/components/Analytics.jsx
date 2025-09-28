import React, { useEffect, useState } from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";
const Analytics = () => {
  const [intel, setIntel] = useState(null);
  useEffect(() => { fetch("/api/project/intel", { method: "POST", body: new URLSearchParams({ project: "Gateway1" }) })
    .then((res) => res.json()).then((data) => setIntel(data)); }, []);
  if (!intel) return <p>Loading analytics...</p>;
  const chartData = [
    { name: "Timeline Risk", value: intel.timeline_risk },
    { name: "Budget Forecast", value: intel.budget_forecast },
    { name: "Resource Efficiency", value: intel.resource_efficiency },
    { name: "Quality Risk", value: intel.quality_risk },
  ];
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}><XAxis dataKey="name" /><YAxis /><Tooltip /><Bar dataKey="value" fill="#a0522d" /></BarChart>
    </ResponsiveContainer>
  );
};
export default Analytics;
