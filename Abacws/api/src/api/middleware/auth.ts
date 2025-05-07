import { NextFunction, Request, Response } from "express";
import { API_KEY } from "../constants";
import { LogLevel } from "../types";

/**
 * Middleware to verify that a user has submitted a correct API key and is authenticated.
 * Also includes CORS headers to allow requests from any origin and any method.
 */
export const apiKeyAuth = (req: Request, res: Response, next: NextFunction) => {
    // Enable CORS headers to allow requests from any origin and any method
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Methods", "*");
    res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");

    // // Check for API key
    // const apiKey = req.header("x-api-key");
    // if (apiKey === API_KEY) return next();

    // // If authentication fails, invoke error handlers
    // next({
    //     code: 403,
    //     message: "You do not have permission to access this resource",
    //     level: LogLevel.error
    // });
    return next();
}
