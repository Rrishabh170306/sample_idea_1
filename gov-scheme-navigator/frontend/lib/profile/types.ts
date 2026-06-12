export type ProfileFormValues = {
  fullName: string;
  dob: string;
  address: string;
  city: string;
  pinCode: string;
  income: string;
  background: 'rural' | 'urban' | '';
  educationBackground: string;
  language: string;
  voiceEnabled: boolean;
};

export type ProfileApiPayload = {
  full_name: string;
  dob: string | null;
  address: string;
  city: string;
  pin_code: string;
  income: number | null;
  background: 'rural' | 'urban' | null;
  education_background: string;
  language: string;
  voice_enabled: boolean;
};

export type ProfileApiResponse = {
  profile: ProfileApiPayload | null;
  identity: {
    email: string | null;
    user_id: string | null;
  };
};

export type ProfileSaveResponse = {
  profile: ProfileApiPayload;
  identity: {
    email: string | null;
    user_id: string | null;
  };
};
