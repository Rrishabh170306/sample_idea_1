export type ChatStatus = 'Thinking' | 'Retrieving' | 'Verifying' | 'Finalizing';

export interface DemoResponse {
  status: ChatStatus;
  text: string;
  citations: Array<{ id: string; label: string; source: string }>;
}

const demoResponses: DemoResponse[] = [
  {
    status: 'Thinking',
    text: 'I am assessing your eligibility context and mapping the most relevant government schemes.',
    citations: [],
  },
  {
    status: 'Retrieving',
    text: 'I am pulling scheme details, benefits, and process guidance from the knowledge base.',
    citations: [],
  },
  {
    status: 'Verifying',
    text: 'I am validating the response against the latest scheme criteria and evidence.',
    citations: [],
  },
  {
    status: 'Finalizing',
    text: 'Based on the current profile assumptions, the strongest matches are PM-KISAN, Kisan Credit Card, and state-level farmer welfare support.\n\n- PM-KISAN provides direct annual support for eligible farmers.\n- Kisan Credit Card supports working capital and farm credit needs.\n- State schemes may vary by district and category requirements.\n\nFor the best result, confirm your landholding, district, and income details.',
    citations: [
      { id: 'c1', label: 'PM-KISAN', source: 'Official PM-KISAN scheme page' },
      { id: 'c2', label: 'KCC Eligibility', source: 'Banking eligibility summary' },
    ],
  },
];

export async function simulateStream(input: string): Promise<AsyncIterable<DemoResponse>> {
  const encoder = new TextEncoder();

  return {
    async *[Symbol.asyncIterator]() {
      for (const step of demoResponses) {
        await new Promise((resolve) => setTimeout(resolve, 450));
        yield step;
      }
    },
  } as AsyncIterable<DemoResponse>;
}
