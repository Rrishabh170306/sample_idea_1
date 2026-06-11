export type ArtifactType = 'eligibility' | 'scheme' | 'comparison' | 'checklist';

export interface MockArtifact {
  id: string;
  type: ArtifactType;
  title: string;
  summary: string;
  status: 'ready' | 'generating' | 'stale';
  details: string[];
  tags?: string[];
}

export const mockArtifacts: MockArtifact[] = [
  {
    id: 'artifact-eligibility',
    type: 'eligibility',
    title: 'Eligibility Report',
    summary: 'Top matches for current profile assumptions.',
    status: 'ready',
    details: ['PM-KISAN: likely fit for eligible farmers.', 'KCC: suitable for working capital and farm credit.'],
    tags: ['eligibility', 'farmer support'],
  },
  {
    id: 'artifact-scheme',
    type: 'scheme',
    title: 'Scheme Detail',
    summary: 'PM-KISAN scheme overview and application notes.',
    status: 'ready',
    details: ['Annual benefit support.', 'Requires farmer identity and bank linkage.', 'Available through official scheme portal.'],
    tags: ['detail', 'application'],
  },
  {
    id: 'artifact-comparison',
    type: 'comparison',
    title: 'Scheme Comparison',
    summary: 'Compare PM-KISAN vs Kisan Credit Card.',
    status: 'ready',
    details: ['PM-KISAN: direct support', 'KCC: credit support', 'Use both for different needs.'],
    tags: ['compare', 'decision support'],
  },
  {
    id: 'artifact-checklist',
    type: 'checklist',
    title: 'Application Checklist',
    summary: 'Documents and actions to prepare for application.',
    status: 'ready',
    details: ['Confirm landholding records.', 'Prepare Aadhaar and bank account details.', 'Check state-specific eligibility notices.'],
    tags: ['checklist', 'documents'],
  },
];

export function getMockArtifact(type: ArtifactType) {
  return mockArtifacts.find((artifact) => artifact.type === type) ?? mockArtifacts[0];
}
