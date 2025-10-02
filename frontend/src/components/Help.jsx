import React from "react";

const faqs = [
  "How to upload documents",
  "How to connect Google Drive",
  "How to use mic and camera inputs",
];

export default function Help() {
  return (
    <section className="mx-auto w-full max-w-4xl px-6 py-10">
      <h2 className="text-2xl font-semibold text-gray-900">Help &amp; FAQ</h2>
      <p className="mt-3 text-gray-600">
        Browse the most common questions below or reach out to the project excellence team for more assistance.
      </p>
      <ul className="mt-6 space-y-3">
        {faqs.map((item) => (
          <li key={item} className="rounded-lg border border-gray-200 bg-white/90 p-4 text-sm text-gray-700 shadow-sm">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
