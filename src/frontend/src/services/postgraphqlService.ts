import { executePostGraphQL } from "./http";

export interface GraphQLPlanNode {
  id: string;
  name: string;
  slug: string;
  monthlyPriceUsd: string;
  monthlyCredits: number;
  dailyRequestLimit: number;
  description: string;
  isActive: boolean;
}

export interface GraphQLAgentNode {
  id: string;
  name: string;
  slug: string;
  systemPrompt: string;
  defaultTier: string;
  defaultTask: string;
  isPublic: boolean;
}

interface PlansQueryResult {
  allBillingPlans: {
    nodes: GraphQLPlanNode[];
  };
}

interface AgentsQueryResult {
  allAgentAgentprofiles: {
    nodes: GraphQLAgentNode[];
  };
}

export const postgraphqlService = {
  async getPlans(): Promise<GraphQLPlanNode[]> {
    const data = await executePostGraphQL<PlansQueryResult>(
      `query GetBillingPlans {
        allBillingPlans(orderBy: ID_ASC) {
          nodes {
            id
            name
            slug
            monthlyPriceUsd
            monthlyCredits
            dailyRequestLimit
            description
            isActive
          }
        }
      }`
    );
    return data.allBillingPlans.nodes;
  },

  async getAgents(): Promise<GraphQLAgentNode[]> {
    const data = await executePostGraphQL<AgentsQueryResult>(
      `query GetAgentProfiles {
        allAgentAgentprofiles(orderBy: ID_ASC) {
          nodes {
            id
            name
            slug
            systemPrompt
            defaultTier
            defaultTask
            isPublic
          }
        }
      }`
    );
    return data.allAgentAgentprofiles.nodes;
  },
};

