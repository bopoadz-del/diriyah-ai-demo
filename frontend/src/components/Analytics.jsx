import React, { useEffect, useState } from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";

const DEFAULT_PROJECT = "Gateway1";

const Analytics = () => {
  const [intel, setIntel] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const fetchIntel = async () => {
      try {
        const response = await fetch("/api/project/intel", {
          method: "POST",
          body: new URLSearchParams({ project: DEFAULT_PROJECT }),
        });
        if (!response.ok) throw new Error(`Intel request failed (${response.status})`);
        const data = await response.json();
        if (isMounted) setIntel(data);
      } catch (intelError) {
        console.error("Failed to load project intel", intelError);
        if (isMounted) setError("Unable to load analytics.");
      }
    };

    fetchIntel();
    return () => { isMounted = false; };
  }, []);

  if (error) return <p className="analytics-error">{error}</p>;
  if (!intel) return <p>Loading analytics…</p>;

  const chartData = [
    { name: "Timeline Risk", value: intel.timeline_risk },
    { name: "Budget Forecast", value: intel.budget_forecast },
    { name: "Resource Efficiency", value: intel.resource_efficiency },
    { name: "Quality Risk", value: intel.quality_risk },
  ];

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <XAxis dataKey="name" interval={0} tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} domain={[0, 100]} />
        <Tooltip />
        <Bar dataKey="value" fill="#a0522d" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
};
export default Analytics;
